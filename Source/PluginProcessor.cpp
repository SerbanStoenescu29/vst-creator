#include "PluginProcessor.h"
#include "PluginEditor.h"

static juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout()
{
    std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;
    params.push_back(std::make_unique<juce::AudioParameterFloat>(
        "delayTime", "Delay Time",
        juce::NormalisableRange<float>(1.0f, 2000.0f, 1.0f), 500.0f));
    return { params.begin(), params.end() };
}

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::mono(), true)
          .withOutput("Output", juce::AudioChannelSet::mono(), true)),
      parameters(*this, nullptr, juce::Identifier("VstAiDemoParams"), createParameterLayout())
{
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    currentSampleRate = sampleRate;
    updateDelayBufferSize();
    delayBuffer.clear();
    delayBufferWritePosition = 0;
}

void VstAiDemoAudioProcessor::releaseResources()
{
    delayBuffer.setSize(1, 1, false, false, true);
}

bool VstAiDemoAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    // Only mono in/out supported
    return layouts.getMainInputChannelSet() == juce::AudioChannelSet::mono()
        && layouts.getMainOutputChannelSet() == juce::AudioChannelSet::mono();
}

void VstAiDemoAudioProcessor::updateDelayBufferSize()
{
    const int maxDelaySamples = static_cast<int>(2.0 * currentSampleRate) + 1; // 2000 ms
    delayBuffer.setSize(1, maxDelaySamples);
    delayBuffer.clear();
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                           juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);

    const int numSamples = buffer.getNumSamples();
    const float* input = buffer.getReadPointer(0);
    float* output = buffer.getWritePointer(0);

    float delayTimeMs = parameters.getRawParameterValue("delayTime")->load();
    int delaySamples = juce::jlimit(1, delayBuffer.getNumSamples() - 1, static_cast<int>(currentSampleRate * delayTimeMs * 0.001f));
    const int delayBufferSize = delayBuffer.getNumSamples();
    float* delayData = delayBuffer.getWritePointer(0);

    for (int i = 0; i < numSamples; ++i)
    {
        int readPosition = delayBufferWritePosition - delaySamples;
        if (readPosition < 0)
            readPosition += delayBufferSize;

        float delayedSample = delayData[readPosition];
        delayData[delayBufferWritePosition] = input[i];
        output[i] = delayedSample;

        delayBufferWritePosition = (delayBufferWritePosition + 1) % delayBufferSize;
    }
}

juce::AudioProcessorEditor* VstAiDemoAudioProcessor::createEditor()
{
    return new VstAiDemoAudioProcessorEditor(*this);
}

void VstAiDemoAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    std::unique_ptr<juce::XmlElement> xml(parameters.copyState().createXml());
    copyXmlToBinary(*xml, destData);
}

void VstAiDemoAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));
    if (xmlState != nullptr)
        parameters.replaceState(juce::ValueTree::fromXml(*xmlState));
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
