#include "PluginProcessor.h"
#include "PluginEditor.h"

SimpleDelayAudioProcessor::SimpleDelayAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::mono(), true)
          .withOutput("Output", juce::AudioChannelSet::mono(), true)),
      apvts(*this, nullptr, "PARAMETERS", createParameterLayout())
{
    delayTimeParam = apvts.getRawParameterValue("delayTime");
    mixParam = apvts.getRawParameterValue("mix");
}

juce::AudioProcessorValueTreeState::ParameterLayout SimpleDelayAudioProcessor::createParameterLayout()
{
    std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;

    params.push_back(std::make_unique<juce::AudioParameterFloat>(
        "delayTime",
        "Delay Time",
        juce::NormalisableRange<float>(1.0f, 2000.0f),
        500.0f));

    params.push_back(std::make_unique<juce::AudioParameterFloat>(
        "mix",
        "Wet/Dry Mix",
        juce::NormalisableRange<float>(0.0f, 100.0f),
        50.0f));

    return { params.begin(), params.end() };
}

void SimpleDelayAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    currentSampleRate = sampleRate;
    delayLine.setMaximumDelayInSamples(static_cast<int>(2.0 * sampleRate));
    delayLine.reset();
}

void SimpleDelayAudioProcessor::releaseResources()
{
    delayLine.reset();
}

bool SimpleDelayAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    const auto input = layouts.getMainInputChannelSet();
    const auto output = layouts.getMainOutputChannelSet();
    return input == output && output == juce::AudioChannelSet::mono();
}

void SimpleDelayAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                             juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);

    if (buffer.getNumChannels() == 0)
        return;

    auto* channelData = buffer.getWritePointer(0);
    auto numSamples = buffer.getNumSamples();

    float delayTimeMs = *delayTimeParam;
    float mixPercent = *mixParam;
    float delayTimeSamples = (delayTimeMs / 1000.0f) * static_cast<float>(currentSampleRate);
    float wetGain = mixPercent / 100.0f;
    float dryGain = 1.0f - wetGain;

    for (int i = 0; i < numSamples; ++i)
    {
        float drySignal = channelData[i];
        delayLine.setDelay(delayTimeSamples);
        
        float wetSignal = delayLine.popSample(0);
        delayLine.pushSample(0, drySignal);

        channelData[i] = drySignal * dryGain + wetSignal * wetGain;
    }
}

juce::AudioProcessorEditor* SimpleDelayAudioProcessor::createEditor()
{
    return new SimpleDelayAudioProcessorEditor(*this);
}

void SimpleDelayAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    auto state = apvts.copyState();
    std::unique_ptr<juce::XmlElement> xml(state.createXml());
    copyXmlToBinary(*xml, destData);
}

void SimpleDelayAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));
    if (xmlState.get() != nullptr)
    {
        if (xmlState->hasTagName(apvts.state.getType()))
        {
            apvts.replaceState(juce::ValueTree::fromXml(*xmlState));
        }
    }
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new SimpleDelayAudioProcessor();
}
