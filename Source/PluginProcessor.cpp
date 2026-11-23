#include "PluginProcessor.h"
#include "PluginEditor.h"

static juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout()
{
    std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;
    params.push_back(std::make_unique<juce::AudioParameterFloat>(
        "delayTime", "Delay Time",
        juce::NormalisableRange<float>(0.0f, 3000.0f, 1.0f, 0.5f), 500.0f));
    params.push_back(std::make_unique<juce::AudioParameterFloat>(
        "mix", "Wet/Dry Mix",
        juce::NormalisableRange<float>(0.0f, 100.0f, 0.1f), 50.0f));
    return { params.begin(), params.end() };
}

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::mono(), true)
          .withOutput("Output", juce::AudioChannelSet::mono(), true)),
      parameters(*this, nullptr, juce::Identifier("MonoDelayParams"), createParameterLayout())
{
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    currentSampleRate = sampleRate;
    updateDelayBufferSize();
    delayBuffer.clear();
    delayBufferWritePos = 0;
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
    // 3 seconds max delay
    int maxDelaySamples = static_cast<int>(currentSampleRate * 3.0) + 1;
    delayBuffer.setSize(1, maxDelaySamples);
    delayBuffer.clear();
    delayBufferWritePos = 0;
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer&)
{
    juce::ScopedNoDenormals noDenormals;
    const int numSamples = buffer.getNumSamples();
    auto* channelData = buffer.getWritePointer(0);

    float delayTimeMs = parameters.getRawParameterValue("delayTime")->load();
    float mixPercent = parameters.getRawParameterValue("mix")->load();
    float wet = mixPercent / 100.0f;
    float dry = 1.0f - wet;

    int delayBufferLength = delayBuffer.getNumSamples();
    int delaySamples = juce::jlimit(0, delayBufferLength - 1, static_cast<int>(currentSampleRate * (delayTimeMs / 1000.0f)));

    auto* delayData = delayBuffer.getWritePointer(0);

    for (int i = 0; i < numSamples; ++i)
    {
        // Write incoming sample to delay buffer
        delayData[delayBufferWritePos] = channelData[i];

        // Calculate read position for delayed sample
        int readPos = delayBufferWritePos - delaySamples;
        if (readPos < 0)
            readPos += delayBufferLength;

        float delayedSample = delayData[readPos];

        // Output is dry + wet*delayed
        channelData[i] = dry * channelData[i] + wet * delayedSample;

        // Advance write position
        delayBufferWritePos = (delayBufferWritePos + 1) % delayBufferLength;
    }
}

juce::AudioProcessorEditor* VstAiDemoAudioProcessor::createEditor()
{
    return new VstAiDemoAudioProcessorEditor(*this);
}

void VstAiDemoAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    auto state = parameters.copyState();
    std::unique_ptr<juce::XmlElement> xml(state.createXml());
    copyXmlToBinary(*xml, destData);
}

void VstAiDemoAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));
    if (xmlState.get() != nullptr)
        if (xmlState->hasTagName(parameters.state.getType()))
            parameters.replaceState(juce::ValueTree::fromXml(*xmlState));
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
